---
name: the-user-does-not-follow-in-real-time
description: "FIRES-WHEN: starting any multi-step job, or about to write a wall of prose — ⭐ The user is AFK and skims: plain words by default, a `## ▶ STEP n of N` banner BEFORE each step, and a live progress line for background work — because silence and a stall look identical from their side"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 3cd75aad-e1c3-4f60-a74f-8e0b72c27165
  modified: 2026-09-23T20:28:15.302Z
---

> Merged 3 memories, bodies kept VERBATIM. Former names (still referenced by other memories): `output-style-plain-default`, `feedback-announce-each-step`, `show-a-live-progress-line`

## output style plain default

Default to **plain mode**: plain words, short sentences, lead with the point, fewer side-notes,
minimal jargon. Front-load the mental model (e.g. a concrete "life of X" walkthrough) before details.

**Why:** the user compared a dense version (tables, nested caveats, "insight" boxes, terms like
at-least-once/liveness/poison-job, inline SQL) against a plain version of the same content and
chose plain as the default. Dense packs more precision per line but costs the reader more per line.

## The bigger half — reinstated 2026-08-11 after it recurred

**The user does not follow the work in real time. Write for someone who does not know what just
happened.** Terseness is not the main failure; **assumed background** is. A compressed line is
unreadable when the reader never saw what it compresses.

Measured example. I wrote:

> "Staging stays alive (I changed the delete-when-done note; B3's re-run needs it). Left healthy —
> policy restored and verified."

Every clause was true and the whole thing was opaque, because it silently assumed four facts the
user had never been told: a throwaway Supabase project exists; a note told them to delete it; the
B3 check failed; a failed check gets re-run later and needs that project. The user had to ask twice
what it meant. The plain version is four short sentences that state those facts in order.

**How to apply:**
- Before a status line, ask: *what must the reader already know for this to parse?* If they were not
  told it in plain words, say it first.
- Name things the first time they appear: not "B3", but "B3 — the check that the serve path does not
  charge twice when a blob read fails".
- Do not put finished work in a list of "things that need you". Say "here is what I changed, FYI".
  A list of decisions should contain only actual decisions.
- Keep concrete artifacts that carry real precision — SQL, exact settings, decision call-outs — but
  wrap them in plain prose, not a wall of matrices.
- Avoid dense-mode defaults (heavy tables, jargon, `★ Insight` boxes) unless the user asks for dense
  or "explanatory" output. This overrides the session's default "explanatory" output style.

## ⭐ Restated by the user 2026-08-28, in their own words

Asked to sort the failure into *words* / *volume* / *continuity*, the user answered:

> "(c) mostly, but (b) too, regarding (a), if you occasionally remind me the definition of the
> acronyms, it will be helpful. Just don't make the prose a mix of unfamiliar terms. Try to be plain
> and straightforward. **No need to use your literary skills**"

Ranked, so the fix is ordered:

1. **Continuity is the biggest failure (c).** They can follow one message and still not hold the
   thread across a day. They do not know what changed while away, or how we got here. This is not
   solved by shorter sentences — it needs a persistent record they can re-read.
2. **Volume, with no signal (b).** Too much text, and no marker for what actually matters.
3. **Terms (a) — smallest, and cheap to fix.** Not "never use them": *re-gloss them periodically*,
   not only on first use, because they forget between sessions. The failure is a sentence that is a
   **mix** of several unfamiliar terms at once.

**"No need to use your literary skills"** — drop the rhetorical constructions: the reversal
("X is not Y; it is Z"), the aphorism, the callback, the dramatic one-line paragraph. They read as
effort spent on style instead of on clarity. Say the thing once, plainly, and stop.

Related: [[name-and-define-every-reference]] (gloss jargon on first use) and [[name-and-define-every-reference]]
(never a bare `#74`) are the same principle applied to terms and to identifiers.

## feedback announce each step

Announce each step **before** starting it, as a visually salient banner — not buried in prose
between tool calls. Settled 2026-09-01 after the user twice interrupted mid-turn: first
*"I am having hard time figuring out what you are currently working on"*, then *"bigger font or
bold, different color would help a lot"*.

The settled format (written into `~/.claude/CLAUDE.md` → *Announce each step before doing it*):

```
## ▶ STEP 3 of 6 — Write the dashboard entry

> **Doing:** appending an entry to the store and regenerating the page.
> **Why:** the gate refuses a branch that changes tracked files and records no entry.
```

**Why:** the user does NOT follow the work in real time — see [[the-user-does-not-follow-in-real-time]].
A wall of tool calls with reasoning scattered between them is unreadable, and mid-turn they
cannot tell *which* step is running. Bold alone was explicitly rejected as not salient enough;
`##` renders large and coloured in the terminal. Arbitrary colour is not available to me.

**How to apply:** state the whole numbered plan once up front, then banner each step as it
starts. Keep **Doing** and **Why** to one line each — the *why* is what makes the plan
followable rather than a bare label. Also: never surface an internal id bare — "Task #206" read
to the user as a shared ticket; say "my own to-do note, not a GitHub issue" or omit the number
([[name-and-define-every-reference]]).

## ⭐ IT LAPSED AGAIN, 2026-09-11, AND THE TRIGGER IS WORTH MORE THAN THE RULE

The user interrupted mid-turn: *"you are not showing your workflow banner anymore"*. Second
recorded lapse; the first is dated in `~/.claude/CLAUDE.md` (2026-09-04).

**Where it broke, exactly:** I bannered STEP 1–6 of a planned slice, then the work turned into
adversarial review rounds — dispatch, read findings, remediate, re-dispatch — and the banners
stopped for roughly fifteen turns. Nothing decided to stop; the plan simply ran out and the review
loop had no numbered steps, so there was nothing to count.

⛔ **THAT IS THE FAILURE MODE: a banner needs a PLAN, and reactive work has none.** Review rounds,
CI watches, and "fix what the reviewer found" are exactly when the user most needs to know what is
happening, and exactly when no numbered plan exists to hang a banner on.

**How to apply:** when work becomes reactive, START A NEW NUMBERED PLAN rather than dropping
banners. *"STEP 1 of 3 — prove the fix reports instead of dying"* is a fine plan invented on the
spot. A one-step plan is still a banner. See also [[never-close-with-a-promise]], which is
the same requirement at the other end of a turn.

## ⭐ THIRD LAPSE, 2026-09-23 — and the user supplied the missing mechanism: SUB-DIVIDE A LONG STEP

The user interrupted twice: *"you are not emitting banners"*, then *"what is the reason you dropped
banner?"*. Third recorded lapse (2026-09-04, 2026-09-11, this one).

**Where it broke, and it is NOT the 2026-09-11 cause.** That lapse was *the plan ran out*. This one
is the opposite: the plan was live and I was inside it. I bannered a 5-step plan, and step 5 —
*"fold the review findings"* — came back carrying **twelve** findings. I kept calling it step 5 and
worked for roughly twenty tool calls with no banner. Nothing ran out; **one step silently expanded
into twelve and I never re-numbered it.**

⛔ **THE RULE THAT WAS MISSING: a step whose size grows past a few tool calls is no longer a step.
Re-plan it, or mark progress inside it.** Waiting for the next planned boundary means going silent
for exactly as long as the step is big — and the bigger the step, the more the user needs to see it.

**The user's own framing, which is the reason this matters beyond etiquette:**

> "banner is to help human to understand what you are doing. And I think the thread history also
> serve to show workflow in goal or dashboard page (we do not have this feature yet). If you have
> very long step between banner, you can sub-divide the long step and emit intermediate progress in
> a one line banner(?) to be compact"

Two things in that:

1. **The banner trail is DATA, not just courtesy.** They expect it to feed a `/goals` or `/dashboard`
   workflow view later. A gap in the trail is a gap in that record — so a missing banner loses
   history, not only attention.
2. **⏳ ON TRIAL, NOT YET STANDARD — a ONE-LINE sub-step marker.** The user's instruction was
   explicit: *"try this in this session and if it is successful, make it a standard process"*. So it
   is a CANDIDATE being exercised on PR #342's round-3 fold; it is **not** in `~/.claude/CLAUDE.md`
   yet and must not be cited as settled. Promote it there only after the user says it worked — and if
   it did not, record what failed instead of quietly keeping it. A full `##` banner per sub-step
   would bury the work it describes. Use the heading banner for the numbered plan steps, and a single
   line for progress inside a long one:

```
▸ 5.3 — ci per-column case added · neutering now reds 10 named cases, no crash
```

**How to apply:**
- Before starting a step, estimate it. More than ~5 tool calls, or more than one finding/file →
  give it its own numbered sub-plan up front (`STEP 5 of 12`), don't nest it invisibly.
- Inside a long step, emit `▸ <n>.<m> — <what just landed> · <the measured fact>` as work completes.
  Carry evidence, same discipline as a progress line: a sub-step marker that only says "working on
  it" is the prose problem with a glyph on the front.
- A step that turns out bigger than planned is RE-NUMBERED, announced as such, not absorbed.

## show a live progress line

**The user asked, twice in three messages:** *"are you continuing or paused right now"*, then
*"show some progress indicator or line so that I can know some job is currently progressing"*.

**The gap.** A background job — a review subagent, `codex-review.py`, a CI run, a 3-minute schema
suite — produces NO output in the user's terminal until it finishes. From their side, "working" and
"stalled" look identical, and the only thing they can do is ask. Saying *"it's running"* in prose
does not fix it, because that is the same sentence a stuck session would emit.

**How to apply — two mechanisms, both cheap.**

1. **Arm a `Monitor` heartbeat for anything that will take more than ~2 minutes.** Its stdout lines
   become notifications in the user's terminal, so they see movement without asking. Emit every
   90-120s, and make each line carry EVIDENCE rather than reassurance — elapsed time, the output
   file's byte count, container/process state. A line that only says "still working" is the prose
   problem with extra steps. Stop it when the job ends.
2. **Print a compact status block in EVERY message while background work is in flight** — one row
   per job, with a state and a measured fact. Keep the same shape each time so it can be scanned.

**What makes a progress line trustworthy:** it must be able to show BAD news. `elapsed 6m · output
0 bytes · container exited` is a useful line; `⏳ working…` is not, because it prints identically
when the thing has died. Derive every field from a live check (`pgrep`, `docker ps`, `ls -la`,
`gh pr checks`), never from what I believe I started.

⚠ Don't poll in a loop myself to produce these — that burns turns and tokens for nothing. The
Monitor emits on its own schedule; my job is to arm it once and read the events.

Related: [[the-user-does-not-follow-in-real-time]] (the user does NOT follow in real time — which is exactly
why silence reads as stalled), [[how-to-shape-a-message-to-me]], [[never-close-with-a-promise]].


## ⭐⭐ FOURTH LAPSE, 2026-10-15 — and the ON-TRIAL sub-step marker was never once used

The user interrupted mid-turn: *"you stop emitting banner and it is hard for me to follow what you
are doing"*. Fourth recorded lapse (2026-09-04, 2026-09-11, 2026-09-23, this one).

**Where it broke.** A 7-step plan was armed and bannered correctly at every heading. Then **step 4
("prove each case can fail") grew into nine separate pieces of work** — close an 11-finding
`check-fixture-variation` red, un-splat 23 call sites, convert 58 cases to thunks, retire one
mutation and add eight, read the declared sum off the guard, run a scoped sweep, run an 88-mutant
ambient sweep, re-measure five figures, reproduce a new fail-open — over roughly **40 tool calls**
with no marker between them. Exactly the 2026-09-23 cause, repeated.

⛔ **THE SHARPER LESSON: the `▸ n.m` marker was recorded as ON TRIAL on 2026-09-23 and I used it
ZERO times in this session.** So the trial never ran, and a rule that is never exercised cannot be
promoted or refuted — it just sits here reading like a decision. **A mechanism recorded as "on
trial" needs a trigger, not a note.** The trigger that would have fired: *a step's second distinct
work item is a sub-step marker*, checked when starting the item rather than when noticing the gap.

**Also skipped, and it is in this same file:** no `Monitor` was armed for two background jobs (a
review subagent and a 20-minute sweep). The *"arm a Monitor for anything over ~2 minutes"* section
above was not applied, and the user's complaint arrived during exactly that silence. Waiting lines
appeared in SOME messages, which is the failure the section describes: inconsistent, so silence and
a stall still look alike.

**How to apply, concretely:**
- When a step produces its **second** distinct deliverable, emit `▸ <n>.<m> — <what landed> ·
  <measured fact>` before starting the next one. Do not wait for the step to end.
- Arm the `Monitor` at the moment the background job is dispatched, in the same message.
- A banner is owed for a step that is PAUSED too — `⏸ PAUSED on <what>` with the waiting line —
  because from the user's side a pause and a stall are the same thing.

## ⏱ EVERY BANNER CARRIES A TIMESTAMP — asked 2026-10-16, and the REASON sets the format

The owner: *"can we add timestamp for each banners. this is to gauge cadence of development"*.

⛔ **THE FORMAT IS `[mm-dd hh:mm]`, PREPENDED. It changed twice inside twenty minutes, so take it
from here and do not re-derive it:**

```
## ▶ [10-16 06:40] STEP 4 of 7 — Re-measure the firing rate
▸ [10-16 06:52] 4.2 — the living corpus re-measured
```

- Square brackets, prepended, `mm-dd hh:mm`. No timezone, no seconds, no `·` separator.
- The DATE is part of it: a session that crosses midnight makes a bare `hh:mm` ambiguous.
- Sub-step markers take it too.

⚠ **The history, because the lesson is not the format.** I first prepended it with a `·` separator
and a timezone, reasoning it should be scannable down the left edge. They asked for it APPENDED in
parentheses. Twenty minutes later: *"changed mind. prepend the timestamp. format [mm-dd hh:mm]"*.
Three states in one hour on one cosmetic detail — so **state the current format and stop arguing for
a version of it**, and when a presentation detail changes again, change it without re-explaining the
previous one. My paragraph defending why prepending suited MY scanning was the wrong kind of
content for a preference that is theirs to set.  exactly what a single step-start time hides.
- ⏳ waiting lines ALREADY require a timestamp with the START, not just a duration
  ([[waiting-lines-carry-a-timestamp]]) — this extends the same rule to every banner.

⚠ **Chat-level only, by choice.** `scripts/begin-plan.py --tick` does NOT stamp a time into the plan
file, so the durable cadence record does not exist yet. Offered rather than built: that script is
mutation-covered and guarded, so stamping each tick is a change with its own gates, and the stated
purpose — gauging cadence while reading — is served by the banner. If they ask for the persistent
version, it is a real slice, not a one-liner.
