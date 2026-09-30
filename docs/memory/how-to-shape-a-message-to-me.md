---
name: how-to-shape-a-message-to-me
description: "FIRES-WHEN: about to write a message to the user — ⭐ How the user wants a message built: LEAD with the conclusion (a heading is not a conclusion), END with a labelled Recommendation / Next action / Filed / Nothing needed, and state READINESS separately from ownership — \"merging stays yours\" READS as \"it's ready\""
metadata:
  type: feedback
---

> Merged 3 memories, bodies kept VERBATIM. Former names (still referenced by other memories): `lead-with-the-conclusion`, `end-prose-with-a-conclusion`, `state-readiness-separately-from-ownership`

## lead with the conclusion

**The user said, reading a summary I was pleased with:** *"Describe clear conclusion first. When I
read your prose, it is hard to capture what you are describing."*

**Why:** the user does NOT follow the work in real time (see [[the-user-does-not-follow-in-real-time]]). They
arrive at a block of prose cold. A section that opens with a pattern, a table, or a narrative of how
I got somewhere forces them to hold unlabelled detail in mind until the meaning arrives — and it
often arrives last, or only by implication. The evidence is not the point; what it establishes is.

**The failure shape, from the actual case.** I wrote a section headed *"The shape worth keeping"*
that opened: *"The same defect appeared three times at shrinking scale, and each instance was
introduced by the fix for the previous one"*, then a three-row table of sentences-vs-code, then the
lesson. Everything in it was true and none of it said, up front, **what I was telling them**.

The conclusion-first version of that same content:

> **Every comment I wrote about this code was wrong in the same way, and the reviews caught it three
> times — so the habit to keep is: don't re-read the sentence, build the world where it should fail
> and run it.** Details: [table] …

**How to apply.**

* **One plain sentence first.** What is true now, or what the user should do. Not what I did, not how
  I got there, not what class of thing it is.
* **A heading is not a conclusion.** *"The shape worth keeping"* names a topic; it makes no claim.
* **Tables and measurements are SUPPORT.** They go after the sentence they support, never before it.
* **Applies per section, not just per message** — every `##` block starts with its own conclusion.
* If I cannot state the conclusion in one sentence, I do not yet know what I am reporting and should
  work that out before writing, rather than narrating my way toward it.

Pairs with [[how-to-shape-a-message-to-me]] — that one governs the CLOSE (a labelled Recommendation /
Next action / Filed / Nothing needed). This one governs the OPEN. Together: say it, show it, then
say what happens next. Related: [[the-user-does-not-follow-in-real-time]] (the same instinct for actions),
[[name-and-define-every-reference]].

### ⟳ RECURRED 2026-09-21 on an EXPLAINER PAGE — and the new part is *what counted as a setup*

The user, asking a question from inside a generated page and then adding:

> *"your prose should be more straightforward. say conclusion first then explain for readability.
> Don't make reader guess"*

**This rule was already written, including *"applies per section"* and *"applies to the brief page
too"*. I broke it anyway, and the reason is worth naming because it did not feel like breaking it.**

The section opened with a **framing device**, not a narrative of my work:

> *"A YAML file contains two kinds of thing that look identical to a regular expression: structure,
> which the file means, and content, which the file merely contains."*

That sentence is true, compact, and the key to everything after it — which is exactly why it felt
like a conclusion. **It is not one.** It defines a distinction and leaves the reader to derive the
answer from it. The reader's actual question — *why did this cause an error?* — is answered only by
inference, three paragraphs later. The heading (*"The one confusion, wearing ten costumes"*) made it
worse: a metaphor promising a payoff still to come.

The repaired opening states the cause, in the plainest words available:

> **The guard tried to work out what a YAML file means by looking at one line at a time, and in YAML
> a line's meaning is not on the line — it is in the lines above it.**

**How to apply, sharpened.** Before any section ships, ask: *if the reader stops after sentence one,
do they have the answer, or do they have the ingredients?* Ingredients are a setup, however elegant.

* **A definition is not a conclusion.** "X is two things, A and B" tells the reader what to hold, not
  what to conclude.
* **An analogy is not a conclusion.** It illustrates a claim; it cannot replace one. Put the claim
  first and let the analogy explain it.
* **A vivid heading raises the debt** — it promises a payoff, so the first sentence must pay it.
* This is the *explanatory* twin of the original case: there I narrated how I got somewhere, here I
  built a lens and made the reader look through it themselves. Both make the reader assemble the
  point. **Do not make the reader assemble the point.**

## end prose with a conclusion

**End every piece of prose with a clear conclusion.** User, 2026-08-18:

> *"so, what is the conclusion? I'd like to have clear conclusion (such as recommendation, next to do
> or add to backlog etc) when you write a prose."*

**Why:** the analysis is not the deliverable — the *decision* is. This user does not follow the work
in real time (see [[the-user-does-not-follow-in-real-time]]), so an answer that ends on a well-reasoned
distinction leaves them holding an unresolved question they now have to re-open. Several threads
today ended with a correct trade-off laid out and no verdict — accurate, and still work for the
reader.

**How to apply.** Close with a labelled block that says which of these it is:

- **Recommendation** — what I would do, stated as a choice, not a menu of options
- **Next action** — what happens now, and who does it
- **Filed** — where it now lives (backlog #N, task #N, an ADR), so it survives compaction
- **Nothing needed** — say that explicitly when it is true; silence reads as an unfinished thought

If a genuine fork remains, name it as one and **give a recommendation anyway** — see
[[putting-a-choice-to-the-user]]. A fork without a recommendation is the analysis handed back.

**Applies to the brief page too**, not just chat: an answer section that ends on nuance has the same
defect. Related: [[name-and-define-every-reference]], [[feedback-flag-transitional-choices]].

## state readiness separately from ownership

**The user said**, after I closed a report with *"Merging #297 stays yours"* while the PR had zero
reviews and a pending check:

> *"if merge is not ready, say it clearly. 'Merging #297 stays yours' appears to indicate that merge
> is ready."*

**The confusion, exactly.** Two different facts get collapsed into one sentence:

| fact | example | changes when? |
|---|---|---|
| **Readiness** — is the work finished and verified? | "reviews done, CI green" | every commit |
| **Ownership** — whose decision is the merge? | "merging is a human gate" | never, it is policy |

*"Merging stays yours"* is the SECOND. Said at the end of a progress report it reads as *"everything
on my side is done, over to you"* — because that is what handing something over normally means. I
had used it as a standing disclaimer and it functioned as a green light.

**How to apply — readiness first, as its own sentence, in plain words.**

* **Not ready:** open with it. *"#297 is NOT ready to merge — it has had no review and `verify` is
  still pending."* Then the list. Never bury it after a wall of green measurements.
* **Ready:** say that too, just as plainly. *"#297 is ready: both review halves clean, CI green."*
  Then, and only then, the ownership line.
* **Never let the ownership line carry the readiness claim.** If the only thing I say about merging
  is whose call it is, the reader infers the work is done.
* Same for any hand-off verb — "over to you", "waiting on you", "your call". Each implies *my* part
  is complete. If it is not, say what is outstanding in the same breath.

⚠ A green CI check is NOT readiness in this repo: `docs/dev-process.md` makes per-task dual
adversarial review the Phase 3 gate, and [[dual-review-what-it-catches]] records a Codex
half passing a branch whose Claude half then found a real defect. "Checks are green" and "ready to
merge" are different claims.

Pairs with [[how-to-shape-a-message-to-me]] (same root cause: the thing the user needs came last, or by
implication) and [[how-to-shape-a-message-to-me]] (the close must be a labelled state + next action,
not a disclaimer). See also [[process-conventions]] for the ownership rule itself.

---

## ⛔ CLOSING A JOB — the house format EXISTS. Use it; do not invent one.

**`docs/process-checklists.md` → *Closing a job: the CHECK / RESULT table* (added 2026-09-04).**
Asked on 2026-09-20 whether a "done protocol" existed, I nearly proposed a new one — it was already
written, in the spine's own checklist file, and I had been closing with prose instead.

Do not close with a paragraph. Close with a table, one row per claim, evidence IN the row:

| check | result |
|---|---|
| Rows 92, 93, 94 exist | ✅ all three |
| Old wording gone | ✅ absent — checked for ABSENCE, not just for the new text |
| Commit | `896f6ef5` |
| Pushed | ✅ same SHA on origin |

**Three rules, and the third is the one that bites:**
1. One row per claim — bundling four assertions means a doubter must re-check all four.
2. Evidence in the row — a SHA, a count, a command's output. Never *"successfully"*.
3. ⛔ **Every row must be a check that COULD have come back ❌.** A table whose rows can only say ✅
   is a decorated assertion, *worse* than the paragraph, because the format implies a verification
   that did not happen.

**Why it beats prose, measured 2026-09-04:** a correct prose report of three filings drew the reply
*"Have you done this too?"* — a paragraph asserting the work is indistinguishable from a paragraph
asserting it wrongly. The same content as a table ended the question. The user's framing:
*"this kind of visible marker is important for comprehensibility."*

Three affordances, three moments: the **step banner** for *what is happening now*, the **option
card** for *what you must decide*, this **table** for *what was actually verified*.
