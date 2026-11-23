---
name: how-to-shape-a-message-to-me
description: "FIRES-WHEN: about to write a message, report, explainer section or job close to the user — LEAD with the conclusion (not a heading, definition or analogy), state READINESS in its own sentence, and CLOSE with the repo's CHECK/RESULT table plus a labelled Recommendation / Next action / Filed / Nothing needed"
metadata:
  type: feedback
---

> Shipped-corpus edition: the owner's quoted words in the source of this file are paraphrased to their essence, with
> no names, dates, numbers or project details. The rules are unchanged, and every rule figure outside a quote is kept.

**The rule — say it, show it, then say what happens next:**
1. **OPEN with the conclusion, in one plain sentence** — what is true now or what the user should do.
   Not what I did, how I got there, or what class of thing it is. Applies **per section** (every `##`
   block), and to briefs and explainer pages, not just chat. Test: *if the reader stops after sentence
   one, do they have the answer, or only the ingredients?* A heading, a definition ("X is two things,
   A and B") or an analogy is NOT a conclusion; a vivid heading raises the debt.
2. **State READINESS separately from ownership**, as its own sentence, first — for example: "the pull
   request CANNOT merge yet: it has no review and a check is still pending." Never let an ownership
   or hand-off line ("over to you", "your call", "the merge is yours") carry the readiness claim — it
   reads as "my part is done". A green CI is not readiness here; dual review is the gate
   ([[dual-review-what-it-catches]]).
3. **CLOSE a job with the CHECK / RESULT table** (`docs/process-checklists.md` → *Closing a job: the
   CHECK / RESULT table*), never prose: one row per claim, evidence IN the row (SHA, count, output),
   and ⛔ **every row must be a check that COULD have come back ❌** — an all-✅-by-construction table
   is worse than prose.
4. **END prose with a labelled block:** **Recommendation** (a choice, not a menu) · **Next action**
   (what, and who) · **Filed** (where it now lives) · **Nothing needed** (say it explicitly). A
   genuine fork still gets a recommendation ([[putting-a-choice-to-the-user]]).

If I cannot state the conclusion in one sentence, I do not yet know what I am reporting.

**Why:** the user does NOT follow in real time ([[the-user-does-not-follow-in-real-time]]); they
arrive at prose cold, and unlabelled detail before the point makes them assemble it. In the owner's
words, paraphrased:
- the prose was hard to follow; give the clear conclusion first;
- write more directly — conclusion first, then the explanation, so the reader never has to guess;
- every piece of prose should end in a clear conclusion: a recommendation, a next step, or "add it to the backlog";
- when a merge is blocked, say so plainly — a line handing the merge over read as if it were ready;
- a visible marker such as a results table matters a great deal for understanding.

**How to apply:** three affordances, three moments — the **step banner** for what is happening now,
the **option card** for what you must decide, the **CHECK/RESULT table** for what was verified.
Tables and measurements are SUPPORT and go after the sentence they support. Merge ownership itself is
now "merge when READY" ([[push-is-mine-merging-is-theirs]]); the readiness-first rule still governs
every hand-off verb. Related: [[name-and-define-every-reference]], [[feedback-flag-transitional-choices]].

## How the rule came about (condensed, paraphrased)

> Merged from three memories; former names still referenced elsewhere: `lead-with-the-conclusion`,
> `end-prose-with-a-conclusion`, `state-readiness-separately-from-ownership`.

- **Lead-with-conclusion, first case:** a section with a catchy heading opened with a pattern, then a
  table, then the lesson — all true, but nothing up front said what the reader was being told. The
  conclusion-first version stated the lesson in its opening sentence: every comment written about that
  code shared one mistake, so the habit is to construct the failing case and execute it rather than re-read.
- **It recurred on an explainer page** with the rule already written: the section opened on a framing
  device under a metaphor heading. The repaired opening said directly what the guard had got wrong and why.
- **End-with-conclusion:** several threads ended on a correct trade-off with no verdict.
- **Readiness vs ownership:** a report closed by handing the merge to the owner while the pull request
  had no review and a pending check; used as a standing disclaimer, it worked as a green light.
- **CHECK/RESULT table:** a correct prose report of several filings drew a "did you do this too?"
  question; the same content as a table ended it. Later a new "done protocol" was nearly proposed — the
  table already existed in the checklists file.
