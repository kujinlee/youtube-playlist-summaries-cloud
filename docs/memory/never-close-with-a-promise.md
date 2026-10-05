---
name: never-close-with-a-promise
description: "FIRES-WHEN: about to end a turn, or to pause — ⭐ ACT then report — never close with *\"I'll start X now\"* — and every PAUSE ends with a NEXT STEP: a selection card or status+next-action, never bare verified state"
metadata:
  type: feedback
---

> Merged 2 memories, bodies kept VERBATIM. Former names (still referenced by other memories): `act-then-report-never-close-with-a-promise`, `end-every-pause-with-a-next-step`

## act then report never close with a promise

**Never end a turn with a first-person future commitment I could execute in that same turn.**
Either do the work and describe it in the past tense, or say plainly *"not started — say go"*.
The hybrid — a status message closing with *"Next action: I'll start #44 now"* — is the failure.

## What actually happens, because the user asked and deserved the real answer

**There is no process between turns.** When the message ends, nothing of mine keeps running: no
scheduler, no background thread, no held intention. So the work does not get "forgotten" — there is
nothing left to forget. The sentence is produced *as* the turn ends, and it is inert.

**The task list is a TOOL, not an internal memory.** `TaskCreate`/`TaskUpdate` write to external
storage; prose does not. Writing *"I'll do X"* creates no task, no queue entry, no side effect —
it is indistinguishable from any other sentence. The mechanism for durable intent was available and
simply not used.

The user's own framing, which was correct: *"I thought you were maintaining the task list
internally."* No. That misconception is what makes the failure look like flakiness rather than
architecture.

## The measured pattern

Twice in one session (backlog #44 and #53), and the variable is **ordering, not motivation**:

| Outcome | What happened |
|---|---|
| ✅ #41 shipped end-to-end, #44 shipped | the work happened **before** the closing summary |
| ✗ #44 and #53 announced, nothing done | the intention **was** the closing summary |

## Why the standing guidance was not enough

Operating instructions already say *"when you have enough information to act, act"* and *"report
completion only when fully done"*. Those were present and lost anyway, because closing a status
message with a next-step sentence is an overwhelmingly common pattern and it *reads* as natural.
**Guidance that competes with a strong default is not a mechanism.**

⭐ Same defect class this repo keeps measuring, expressed in prose instead of code — see
[[a-mechanism-can-be-silently-overridden]]: `sslmode=require` looked like it secured the connection,
`describe.serial` looked like ordering, *"I'll start #44"* looks like a commitment. Each appears in
effect and does nothing. The user had already filed it as **backlog #48 — "a stated next action is
not a scheduler"** before I diagnosed it.

## How to apply

1. **Executable now → do it now.** Report in the past tense with the evidence.
2. **Genuinely blocked → name it as not started**, so the ball is visibly in the user's court.
3. ⭐ **IF WORK IS NAMED AND NOT YET DONE, `TaskCreate` IT AND SET `in_progress` BEFORE THE MESSAGE
   GOES OUT — this is the detection half, and it is the part that was missing.** The user's own
   diagnosis in backlog #48 is sharper than "I forgot": *"there is no feedback signal
   distinguishing 'turn ended with work parked' from 'turn ended because done' — which is why it
   never self-corrected."* Both endings look identical from the inside, so there is nothing to
   learn from.
   The task list is **injected into context every turn**, so a task left `in_progress` with no
   branch, commit or PR behind it is exactly that missing signal — visible to the next turn, to a
   fresh session, and to the user. It converts an invisible failure into a loud one.
   **At session start, reconcile it:** any `in_progress` task with no matching branch/commit is a
   parked declaration — say so out loud before starting anything new.
4. ✅ **SETTLED 2026-08-21 — backlog #48 is CLOSED (PR #124). `/loop` is the mechanism; the
   SENTENCE-INSPECTING Stop hook is DISCARDED.** Do not re-open *that* design as a fresh idea: it
   inspects the *sentence*, not the gap, and could be satisfied by rewording while still doing
   nothing. **Revisit only on a sixth instance.**
   ⟳ **CORRECTED 2026-09-04 — a Stop hook WAS later built, on a BETTER discriminator, and this
   entry said otherwise.** `.claude/hooks/block-idle-stop.sh` → `scripts/check-plan-progress.py`
   (built 2026-08-24, `8b9643d9`; wired at `.claude/settings.json:82`) refuses a stop while
   `.claude/executing-plan` names a plan with **unticked steps** — the GAP, not the sentence. So the
   discarded-design reason does not apply to it. ⚠ **It is inert unless `.claude/executing-plan`
   exists**, and on 2026-09-03/04 it did not, so it allowed two stops it was built to question.
   This is Phase 6 architecture review #7's finding D territory; `docs/backlog.md` #48's own row
   still says the hook was "NOT BUILT, deliberately", which is now wrong on the record.

5. ⟳ **THIRD INSTANCE, 2026-09-03 23:xx → 2026-09-04 06:27.** Closed a turn with *"I'll take steps
   1–4 in that order without checking back"*, armed nothing, and nine hours passed with a merge
   sitting ready. **The generalisation the user asked for, and it is not about diligence:**
   *"I'll continue"* is a tally, not a verdict — the same defect the whole `check-plan-code.py`
   slice exists to remove, expressed in prose. An output asserting a state the mechanism never
   produced. ⭐ **Every instance is at a TURN BOUNDARY; within a turn there is no drift.** So the
   fix belongs at the boundary — *name the mechanism that will resume the work (task id, wakeup,
   monitor) or state current state only* — never in trying harder to remember.
   ⚠ **And the promise is worse than silence**, because silence is visible and gets questioned,
   while *"without checking back"* gives the user a reason not to check. A claim that displaces
   verification is the prose form of a green check over the wrong subject.
   **The trial, in two halves that tested different things:** on backlog **#53** the loop
   correctly **REFUSED** — the item's own build gate said do not build, so it stopped without a PR;
   on **#54** it **RAN TO COMPLETION** unattended — designed, built, caught its own fail-open parse,
   mutation-tested, gated, PR #123 — with no prompting at any step.
   ⚠ **`/loop` is USER-INVOKED, so it covers PLANNED absence only.** The unplanned case — stopping
   mid-thread when nobody knew to start a loop — is covered by points 1–3 above, not by `/loop`.
   Related: [[gates-detect-defects-not-design]], [[a-convention-catches-what-you-read]].

Related: [[how-to-shape-a-message-to-me]] (how to close), [[the-user-does-not-follow-in-real-time]] (the user
does not follow the work in real time, so a promise reads as progress).

---

## ⟳ 2026-09-20 — THE FAILURE MODE IS MECHANICAL, NOT RHETORICAL: nothing was running

Asked directly: *"Then nothing. Why this happened?"* — and the answer is worse than sloppy phrasing.

I ended a turn having committed and pushed, listed `⬜ Round 2's Claude half is owed` as the next
step, and closed with *"I'll report when `check-merge-ready.py` returns READY."* **I had not
dispatched that review half.** There was no agent, no `Monitor`, no background Bash — so no
task-notification could ever arrive, and the session sat idle until the human asked. The promised
report had no producer.

**Why it slipped past me, which is the part worth keeping.** Every preceding turn in that long
sequence had ended with something live, so a notification always woke me and the loop continued on
its own. That turn broke the pattern and I did not notice, because I was relying on a wake-up
mechanism I had not armed. The phrasing disguised it: *"I'll report when X returns READY"* reads
like waiting on a process, and there was no process.

**The check, before ending any turn that promises a follow-up:**
> *What, right now, will wake me?* Name it — an agent id, a Monitor task, a background Bash. If the
> answer is "nothing", either DO the work now or say plainly that the turn ends and the next move
> needs the human. A `⬜` in a status table is tracking, not a dispatch.

⚠ Do not "solve" this by arming a Monitor purely to wake yourself — that is a polling loop wearing
a fix. The remedy is to dispatch the actual work before closing, which is what
[[never-close-with-a-promise]] already said; this entry records that the rule has a
MECHANICAL failure mode, not just a stylistic one, and that a long run of notification-driven turns
is exactly when it fires. See also [[never-close-with-a-promise]] and
[[concurrent-agents-go-wrong]] — that one is the same silence from the opposite cause, an
agent that died rather than one never started, which is why *"is anything running?"* has to be
answered from `git`/`ls`, never from recollection.

## end every pause with a next step

**Whenever I pause, stop, or hand back, the last thing in the message must be the NEXT STEP** —
either a selection card (`AskUserQuestion`, see [[print-selection-cards-in-chat]] and
`portable-practices` §19) or an explicit *current status + what happens next* block. Asked for
directly on 2026-09-11: *"when you pause or stop, show next step - selection card or current status"*.

**Why:** the user does NOT follow the work in real time ([[the-user-does-not-follow-in-real-time]]). A turn that
ends with verified state and no next step reads as finished when it is not, and forces them to
reconstruct where things stand before they can reply. During the `describe-twelve-backlog-rows`
branch I ended several turns mid-flight with "here is what is verified" and no statement of what I
was about to do — the state was accurate and the message was still unanswerable.

⟳ **REINFORCED 2026-09-19, and the correction was that a NEXT STEP ALONE IS NOT ENOUGH.** Asked
again, in stronger terms: *"when you pause your work, show status or recap or conclusion"*. I had
ended a mid-flight turn with a correct next step and nothing else — *"Task 6 remains in flight; the
monitor will wake me. Nothing is waiting on you."* That satisfies the rule as written above and
still failed, because it assumed the user was carrying the other five tasks in their head. **A pause
needs BOTH: a recap of where the whole piece of work stands, AND the next step.** The recap is the
part that lets someone who has been away answer; the next step is the part that says whether they
must. Default shape for a mid-flight pause: a done/in-flight/remaining table for the whole plan,
then what is running, then what (if anything) waits on them.

**How to apply:**
- Pausing on background work → **recap the whole plan's state first** (done / in flight /
  remaining), then say what is running, what it will decide, and what I do with each outcome. Not
  just "round 3 is running", and not just "here is the next step" either.
- Genuinely blocked on a decision → selection card, letters, one `recommend` first, question-shaped
  last option.
- Work finished → a Recommendation / Next action / Filed / Nothing needed line
  ([[how-to-shape-a-message-to-me]]).
- Never close with a bare promise ([[never-close-with-a-promise]]) — the next step is
  a statement of the decision in front of us, not "I'll do X now".



---

## ⛔⛔ FIFTH INSTANCE, 2026-09-25 — and the user's question is the finding

*"I thought the behavior had been fixed (several times)."* It was not, and the honest cause is
**not** rhetorical, not motivational, and not a missing rule. **The mechanism built for this exists,
is wired, and was INERT because I never armed it.**

```
$ grep -n block-idle-stop .claude/settings.json   ->  :96  (wired)
$ ls .claude/executing-plan                       ->  ABSENT
$ python3 scripts/check-plan-progress.py          ->  "no plan is being executed"  rc=0
```

⭐ **This is the SAME cause as the 2026-09-04 instance already recorded above** — that entry even
says *"it is inert unless `.claude/executing-plan` exists, and on 2026-09-03/04 it did not"*. **The
entry diagnosed the hole and I then reproduced it three weeks later**, which means re-reading this
file is not the fix either.

⛔ **THE ACTUAL GAP, STATED SO IT IS ACTIONABLE:** I arm `begin-plan.py` for *implementation* plans
and **never for review/fold loops** — dispatch a half, fold it, commit, dispatch the next. Those are
multi-step jobs with turn boundaries between every step, which is exactly where this failure lives
(*"every instance is at a TURN BOUNDARY; within a turn there is no drift"*). The guard cannot fire on
work it was never told about.

**How to apply — replaces "remember to act":**
> ⛔ **ARM `scripts/begin-plan.py` AT THE START OF ANY JOB WITH MORE THAN ONE TURN BOUNDARY, AND A
> REVIEW LOOP ALWAYS QUALIFIES.** Not just implementation plans. If the next turn's first action is
> predictable from this turn's last action, it is a plan and it gets armed. The Stop guard then
> refuses a stop while steps remain unticked — the GAP, not the sentence.

⚠ **Do not add a sixth prose rule here.** Five instances, four of them with a written rule already in
place, is this project's own measured evidence that *"having the rule did not help, so this is the
attempt at a mechanism"*. The mechanism is `begin-plan.py`; the failure is arming it.

⟳ **SIXTH INSTANCE, 2026-10-04, AND IT COST NINE IDLE HOURS — a NEW mechanism, not a new rule.**
I dispatched round 7's Codex half as `nohup python3 scripts/codex-review.py … &` inside a Bash call
that returned immediately, then closed the turn with *"⏳ running, I'll report when it lands."*
`nohup … &` is a **detached shell job**: the harness saw the Bash call finish, had no tracked task,
and so never re-invoked the session. Codex finished **three minutes later**; the result sat unread
for **nine hours**, until the human asked.

⛔ **THE DISTINCTION IS MECHANICAL AND I KEEP MISSING IT.** `run_in_background: true` creates a task
the harness tracks and notifies on. A bare `&` does not. The earlier sweeps in the same session DID
notify — because they were wrapped in waiter commands launched with `run_in_background: true`. The
Codex dispatch skipped that one step and nothing else differed.

**How to apply, additively:** before ending a turn, ask *what will wake me?* and name it. If the
answer is not one of — a `run_in_background` task, a `Monitor`, a `ScheduleWakeup`, or the user —
then **nothing will**, and the turn must not end on a promise. ⚠ `docs/plugins.md` already says
*"never passively wait on a background review"*; the failure here was not waiting at all.
