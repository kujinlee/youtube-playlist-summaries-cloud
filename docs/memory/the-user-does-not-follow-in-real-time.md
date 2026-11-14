---
name: the-user-does-not-follow-in-real-time
description: "FIRES-WHEN: starting any multi-step job, a step grows past a few tool calls, work turns reactive (review rounds, CI, fixes), or about to write a wall of prose — the user is AFK and skims: plain words, a timestamped `## ▶` banner BEFORE each step, `▸` sub-step lines inside long steps, and a progress line that can show bad news"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 3cd75aad-e1c3-4f60-a74f-8e0b72c27165
  modified: 2026-09-23T20:28:15.302Z
---

> Merged from three memories. Former names (still referenced by other memories): `output-style-plain-default`,
> `feedback-announce-each-step`, `show-a-live-progress-line`.

**The current rule:**
1. **Write for someone who does not know what just happened.** Plain words, short sentences, lead with the point.
   Before a status line ask *what must the reader already know for this to parse?* and say that first. Name things
   in full the first time ("B3 — the check that the serve path does not charge twice…"), and **re-gloss** terms
   periodically, not only on first use. No dense-mode defaults (heavy tables, `★ Insight` boxes, jargon mixes) unless
   asked — this overrides the session's "explanatory" output style. No rhetorical constructions (reversals,
   aphorisms, dramatic one-line paragraphs). Finished work is FYI, never in a "needs you" list.
2. **Banner every step BEFORE starting it.** The authoritative format is `~/.claude/CLAUDE.md` → *Announce each step
   before doing it* — take it from there, do not re-derive it: `## ▶ [mm-dd hh:mm] STEP n of N — …` with **Thread**,
   **Doing**, **Why** lines; timestamp from `date`. State the whole numbered plan once up front.
3. **A step that grows is re-planned or sub-marked.** When a step produces its **second** distinct deliverable, emit
   `▸ [mm-dd hh:mm] n.m — <what landed> · <measured fact>` before starting the next one. More than ~5 tool calls or more
   than one finding/file → give it a numbered sub-plan up front. (Started on trial 2026-09-23; now part of the
   CLAUDE.md banner spec.)
4. **Reactive work gets a plan too.** Review rounds, CI watches, "fix what the reviewer found" have no numbered steps,
   so invent one on the spot ("STEP 1 of 3 — …"); a one-step plan is still a banner. A paused step gets
   `⏸ PAUSED on <what>` plus the waiting line.
5. **Background work gets a progress signal that can show BAD news.** A compact status block in every message while
   work is in flight — one row per job, a state and a measured fact derived from a live check (`pgrep`, `docker ps`,
   `ls -la`, `gh pr checks`), never from what I believe I started. `elapsed 6m · output 0 bytes · container exited`
   is useful; `⏳ working…` is not. ⚠ How to *watch* has a cost: a Monitor's every wake is a model turn — see
   [[no-question-watch-while-owner-afk]] for when a one-shot background poll is cheaper; never poll in a loop myself.

**Why:** the user does not follow the work in real time; silence and a stall look identical from their side. Their
own ranking (2026-08-28) — continuity is the biggest failure, then volume without signal, then terms:

> "(c) mostly, but (b) too, regarding (a), if you occasionally remind me the definition of the
> acronyms, it will be helpful. Just don't make the prose a mix of unfamiliar terms. Try to be plain
> and straightforward. **No need to use your literary skills**"

And on banners (2026-09-23) — the banner trail is DATA, not just courtesy:

> "banner is to help human to understand what you are doing. And I think the thread history also
> serve to show workflow in goal or dashboard page (we do not have this feature yet). If you have
> very long step between banner, you can sub-divide the long step and emit intermediate progress in
> a one line banner(?) to be compact"

**How to apply:** check at the START of each work item whether it is a new step or sub-step — the gap is never noticed
from inside it. Never surface an internal id bare ("Task #206" read as a shared ticket) —
[[name-and-define-every-reference]]. Related: [[how-to-shape-a-message-to-me]], [[never-close-with-a-promise]],
[[waiting-lines-carry-a-timestamp]].

## History
- **Plain mode chosen** after the user compared a dense and a plain version of the same content. **Reinstated
  2026-08-11:** "Staging stays alive (I changed the delete-when-done note; B3's re-run needs it)…" silently assumed four
  facts the user had never been told; they asked twice what it meant.
- **Banners settled 2026-09-01** after *"I am having hard time figuring out what you are currently working on"* and
  *"bigger font or bold, different color would help a lot"* (bold alone rejected; `##` renders large and coloured).
- **Four recorded lapses**, each a different trigger: 2026-09-04 (a script printed the banner to Bash stdout, which the
  user doesn't see — dated in `~/.claude/CLAUDE.md`); 2026-09-11 *"you are not showing your workflow banner anymore"* —
  the plan ran out and ~15 turns of review rounds had no banner; 2026-09-23 *"you are not emitting banners"* /
  *"what is the reason you dropped banner?"* — step 5 grew to twelve findings over ~20 tool calls, never re-numbered;
  2026-10-15 *"you stop emitting banner and it is hard for me to follow what you are doing"* — step 4 grew into nine
  pieces over ~40 tool calls, and the on-trial `▸` marker had been used ZERO times (a mechanism "on trial" needs a
  trigger, not a note). No Monitor was armed for a review subagent or a 20-minute sweep either.
- **Progress line asked for** in two messages: *"are you continuing or paused right now"*, then *"show some progress
  indicator or line so that I can know some job is currently progressing"*. The original mechanism was a Monitor
  heartbeat every 90–120 s for jobs over ~2 minutes.
- **Timestamp asked 2026-10-16:** *"can we add timestamp for each banners. this is to gauge cadence of development"*;
  the format changed three times in an hour (`·`+timezone → appended in parentheses → *"changed mind. prepend the
  timestamp. format [mm-dd hh:mm]"*). Lesson: a presentation preference is theirs to set — state it, don't argue.
  `scripts/begin-plan.py --tick` does not stamp a time into the plan file; a durable cadence record would be its own
  slice.
