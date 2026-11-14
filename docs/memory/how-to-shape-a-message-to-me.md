---
name: how-to-shape-a-message-to-me
description: "FIRES-WHEN: about to write a message, report, explainer section or job close to the user — LEAD with the conclusion (not a heading, definition or analogy), state READINESS in its own sentence, and CLOSE with the repo's CHECK/RESULT table plus a labelled Recommendation / Next action / Filed / Nothing needed"
metadata:
  type: feedback
---

**The rule — say it, show it, then say what happens next:**
1. **OPEN with the conclusion, in one plain sentence** — what is true now or what the user should do.
   Not what I did, how I got there, or what class of thing it is. Applies **per section** (every `##`
   block), and to briefs and explainer pages, not just chat. Test: *if the reader stops after sentence
   one, do they have the answer, or only the ingredients?* A heading, a definition ("X is two things,
   A and B") or an analogy is NOT a conclusion; a vivid heading raises the debt.
2. **State READINESS separately from ownership**, as its own sentence, first: *"#297 is NOT ready to
   merge — no review, `verify` pending."* Never let an ownership or hand-off line ("over to you",
   "your call", "merging stays yours") carry the readiness claim — it reads as "my part is done". A
   green CI is not readiness here; dual review is the gate ([[dual-review-what-it-catches]]).
3. **CLOSE a job with the CHECK / RESULT table** (`docs/process-checklists.md` → *Closing a job: the
   CHECK / RESULT table*), never prose: one row per claim, evidence IN the row (SHA, count, output),
   and ⛔ **every row must be a check that COULD have come back ❌** — an all-✅-by-construction table
   is worse than prose.
4. **END prose with a labelled block:** **Recommendation** (a choice, not a menu) · **Next action**
   (what, and who) · **Filed** (where it now lives) · **Nothing needed** (say it explicitly). A
   genuine fork still gets a recommendation ([[putting-a-choice-to-the-user]]).

If I cannot state the conclusion in one sentence, I do not yet know what I am reporting.

**Why:** the user does NOT follow in real time ([[the-user-does-not-follow-in-real-time]]); they
arrive at prose cold, and unlabelled detail before the point makes them assemble it. The owner's words:
- *"Describe clear conclusion first. When I read your prose, it is hard to capture what you are describing."*
- 2026-09-21: *"your prose should be more straightforward. say conclusion first then explain for readability. Don't make reader guess"*
- 2026-08-18: *"so, what is the conclusion? I'd like to have clear conclusion (such as recommendation, next to do or add to backlog etc) when you write a prose."*
- *"if merge is not ready, say it clearly. 'Merging #297 stays yours' appears to indicate that merge is ready."*
- 2026-09-04, on the table: *"this kind of visible marker is important for comprehensibility."*

**How to apply:** three affordances, three moments — the **step banner** for what is happening now,
the **option card** for what you must decide, the **CHECK/RESULT table** for what was verified.
Tables and measurements are SUPPORT and go after the sentence they support. Merge ownership itself is
now "merge when READY" ([[push-is-mine-merging-is-theirs]]); the readiness-first rule still governs
every hand-off verb. Related: [[name-and-define-every-reference]], [[feedback-flag-transitional-choices]],
[[process-conventions]].

## History (condensed)

> Merged from three memories; former names still referenced elsewhere: `lead-with-the-conclusion`,
> `end-prose-with-a-conclusion`, `state-readiness-separately-from-ownership`.

- **Lead-with-conclusion, first case:** a section headed *"The shape worth keeping"* opened with a
  pattern, a three-row table, then the lesson — all true, none of it said up front what I was telling
  them. Conclusion-first version: *"Every comment I wrote about this code was wrong in the same way …
  so the habit to keep is: don't re-read the sentence, build the world where it should fail and run it."*
- **Recurred 2026-09-21 on an explainer page**, with the rule already written: the section opened on a
  framing device (*"A YAML file contains two kinds of thing that look identical to a regular
  expression …"*) under a metaphor heading (*"The one confusion, wearing ten costumes"*). Repaired
  opening: *"The guard tried to work out what a YAML file means by looking at one line at a time, and
  in YAML a line's meaning is not on the line — it is in the lines above it."*
- **End-with-conclusion, 2026-08-18:** several threads ended on a correct trade-off with no verdict.
- **Readiness vs ownership:** I closed a report with *"Merging #297 stays yours"* while #297 had zero
  reviews and a pending check; used as a standing disclaimer, it functioned as a green light.
- **CHECK/RESULT table, 2026-09-04:** a correct prose report of three filings drew *"Have you done
  this too?"*; the same content as a table ended the question. On 2026-09-20 I nearly proposed a new
  "done protocol" — the table was already in the checklists file.
