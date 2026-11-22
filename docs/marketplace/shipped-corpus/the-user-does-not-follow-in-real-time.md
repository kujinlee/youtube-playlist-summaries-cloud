---
name: the-user-does-not-follow-in-real-time
description: "FIRES-WHEN: starting any multi-step job, a step grows past a few tool calls, work turns reactive (review rounds, CI, fixes), or about to write a wall of prose — the user is AFK and skims: plain words, a timestamped `## ▶` banner BEFORE each step, `▸` sub-step lines inside long steps, and a progress line that can show bad news"
metadata:
  type: feedback
---

> Shipped-corpus edition: the owner's quoted words in the source of this file are paraphrased to their essence, with
> no names, dates, numbers or project details. The rules are unchanged, and every rule figure outside a quote is kept.

> Merged from three memories. Former names (still referenced by other memories): `output-style-plain-default`,
> `feedback-announce-each-step`, `show-a-live-progress-line`.

**The current rule:**
1. **Write for someone who does not know what just happened.** Plain words, short sentences, lead with the point.
   Before a status line ask *what must the reader already know for this to parse?* and say that first. Name things
   in full the first time (the check's name AND what it checks), and **re-gloss** terms periodically, not only on
   first use. No dense-mode defaults (heavy tables, insight boxes, jargon mixes) unless asked — this overrides any
   "explanatory" output style. No rhetorical constructions (reversals, aphorisms, dramatic one-line paragraphs).
   Finished work is FYI, never in a "needs you" list.
2. **Banner every step BEFORE starting it.** The authoritative format is the user's global instructions file →
   *Announce each step before doing it* — take it from there, do not re-derive it: `## ▶ [mm-dd hh:mm] STEP n of N — …`
   with **Thread**, **Doing**, **Why** lines; timestamp from `date`. State the whole numbered plan once up front.
3. **A step that grows is re-planned or sub-marked.** When a step produces its **second** distinct deliverable, emit
   `▸ [mm-dd hh:mm] n.m — <what landed> · <measured fact>` before starting the next one. More than ~5 tool calls or
   more than one finding/file → give it a numbered sub-plan up front.
4. **Reactive work gets a plan too.** Review rounds, CI watches, "fix what the reviewer found" have no numbered steps,
   so invent one on the spot ("STEP 1 of 3 — …"); a one-step plan is still a banner. A paused step gets
   `⏸ PAUSED on <what>` plus the waiting line.
5. **Background work gets a progress signal that can show BAD news.** A compact status block in every message while
   work is in flight — one row per job, a state and a measured fact derived from a live check (`pgrep`, `docker ps`,
   `ls -la`, `gh pr checks`), never from what I believe I started. `elapsed 6m · output 0 bytes · container exited`
   is useful; `⏳ working…` is not. ⚠ How to *watch* has a cost: a Monitor's every wake is a model turn — see
   [[no-question-watch-while-owner-afk]] for when a one-shot background poll is cheaper; never poll in a loop myself.

**Why:** the user does not follow the work in real time; silence and a stall look identical from their side. Their
own ranking — continuity is the biggest failure, then volume without signal, then terms. Paraphrased: an occasional
reminder of what an acronym means helps; prose should not be a mix of unfamiliar terms; be plain and direct, with no
literary flourishes.

And on banners — the banner trail is DATA, not just courtesy. Paraphrased: the banner exists so a human can see what
is being done, and the history of threads could later feed a workflow view on a goal or dashboard page; a very long
step between banners can be split, with compact one-line progress markers in between.

**How to apply:** check at the START of each work item whether it is a new step or sub-step — the gap is never noticed
from inside it. Never surface an internal id bare (a bare task number reads as a shared ticket) —
[[name-and-define-every-reference]]. Related: [[how-to-shape-a-message-to-me]], [[never-close-with-a-promise]],
[[waiting-lines-carry-a-timestamp]].

## How the rule came about (paraphrased)
- **Plain mode was chosen** after the user compared a dense and a plain version of the same content. It was
  reinstated when a short status line silently assumed four facts the user had never been told, and they asked twice
  what it meant.
- **Banners were settled** after the user said they could not tell what was being worked on, and asked for something
  larger or more visible than bold text (a `##` heading renders large and coloured).
- **Four recorded lapses**, each a different trigger: a script printed the banner to tool output, which the user
  does not see; the plan ran out and ~15 turns of review rounds had no banner; a step grew to twelve findings over ~20
  tool calls and was never re-numbered; a step grew into nine pieces over ~40 tool calls, and the sub-step marker,
  then only "on trial", had been used ZERO times (a mechanism on trial needs a trigger, not a note). No Monitor was
  armed for a review subagent or a 20-minute sweep either.
- **A progress line was asked for** when the user could not tell whether work was continuing or paused. The first
  mechanism was a Monitor heartbeat every 90–120 s for jobs over ~2 minutes.
- **Timestamps were asked for** to gauge the cadence of development; the format changed three times in an hour
  before settling on a prepended `[mm-dd hh:mm]`. Lesson: a presentation preference is the user's to set —
  state it, don't argue.
