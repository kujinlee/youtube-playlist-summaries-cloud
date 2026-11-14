---
name: never-close-with-a-promise
description: "FIRES-WHEN: about to end a turn, or to pause — ⭐ ACT then report — never close with *\"I'll start X now\"* — and every PAUSE ends with a NEXT STEP: a selection card or status+next-action, never bare verified state"
metadata:
  type: feedback
---

> Merged 2 memories. Former names (still referenced by other memories): `act-then-report-never-close-with-a-promise`, `end-every-pause-with-a-next-step`

## The rule (current)

1. **Never end a turn with a first-person future commitment I could execute in that same turn.** Do the work and
   report it in the past tense, or say plainly *"not started — say go"*.
2. **Before ending any turn that promises a follow-up, answer: _what, right now, will wake me?_** Name it — an agent
   id, a `run_in_background` Bash task, a `Monitor`, a scheduled wakeup, or the user. If the answer is "nothing",
   DO the work now, or say the turn ends and the next move needs the human. A `⬜` in a status table is tracking,
   not a dispatch. ⛔ A bare `nohup … &` is NOT tracked — the harness never re-invokes on it; use
   `run_in_background: true`.
3. ⛔ **ARM `scripts/begin-plan.py` AT THE START OF ANY JOB WITH MORE THAN ONE TURN BOUNDARY — a review/fold loop
   always qualifies**, not just implementation plans. The Stop guard (`.claude/hooks/block-idle-stop.sh` →
   `scripts/check-plan-progress.py`) refuses a stop while the armed plan has unticked steps — the GAP, not the
   sentence. ⚠ It is INERT unless `.claude/executing-plan` exists.
4. **Named-but-not-done work gets a task (`TaskCreate`, `in_progress`) before the message goes out.** At session
   start, any `in_progress` task with no branch/commit behind it is a parked declaration — say so out loud.
5. **Every pause ends with a RECAP + a NEXT STEP.** Recap the whole plan (done / in flight / remaining), say what is
   running and what each outcome leads to, then either a selection card ([[print-selection-cards-in-chat]]) or an
   explicit *status + what happens next*. Work finished → a Recommendation / Next action / Filed / Nothing needed
   line ([[how-to-shape-a-message-to-me]]).

**Why:** there is no process between turns — a sentence like *"I'll report when X returns"* has no producer unless
something was armed. Every instance has been at a TURN BOUNDARY; within a turn there is no drift. And a promise is
worse than silence: silence gets questioned, *"without checking back"* gives the user a reason not to check. The
user does not follow in real time ([[the-user-does-not-follow-in-real-time]]), so a promise reads as progress.

**How to apply:** ⚠ do not add another prose rule here — six instances, most with a written rule already in place,
is the evidence that remembering does not work; the mechanism is arming `begin-plan.py` and naming the waker.
Do not "solve" it by arming a Monitor purely to wake yourself — dispatch the actual work. *"Is anything running?"*
is answered from `git`/`ls`/task state, never recollection ([[concurrent-agents-go-wrong]]).

User's words: *"when you pause or stop, show next step - selection card or current status"* (2026-09-11);
*"when you pause your work, show status or recap or conclusion"* (2026-09-19); *"I thought you were maintaining the
task list internally."*; *"Then nothing. Why this happened?"* (2026-09-20); *"I thought the behavior had been fixed
(several times)."* (2026-09-25).

Related: [[a-mechanism-can-be-silently-overridden]] (*"I'll start #44"* looks like a commitment and does nothing —
same class as `sslmode=require`), [[gates-detect-defects-not-design]], [[a-convention-catches-what-you-read]].

## History

- **Instances 1–2 (backlog #44, #53):** the variable was ORDERING — #41 and #44 shipped when the work happened before
  the closing summary; #44/#53 announced and not done when the intention WAS the summary. The user filed backlog #48
  *"a stated next action is not a scheduler"*: *"there is no feedback signal distinguishing 'turn ended with work
  parked' from 'turn ended because done' — which is why it never self-corrected."*
- **2026-08-21:** backlog #48 CLOSED (PR #124) with `/loop` as the mechanism; a SENTENCE-inspecting Stop hook was
  discarded (rewording satisfies it). `/loop` is user-invoked, so it covers PLANNED absence only. Trial: on #53 the
  loop correctly REFUSED (the item's build gate said no); on #54 it ran to completion unattended (PR #123).
- **Corrected 2026-09-04:** a Stop hook WAS built on a better discriminator — `block-idle-stop.sh` →
  `check-plan-progress.py` (built 2026-08-24, `8b9643d9`), which reads unticked plan steps. It was inert on
  2026-09-03/04 because `.claude/executing-plan` was absent.
- **Third instance, 2026-09-03 → 09-04 06:27:** closed with *"I'll take steps 1–4 in that order without checking
  back"*, armed nothing; nine hours passed with a merge ready.
- **2026-09-20:** promised *"I'll report when `check-merge-ready.py` returns READY"* with no review half dispatched
  — no agent, Monitor or background Bash existed. A long run of notification-driven turns is exactly when this fires.
- **Fifth instance, 2026-09-25:** hook wired, `.claude/executing-plan` ABSENT, `check-plan-progress.py` → "no plan is
  being executed" rc=0. Cause: `begin-plan.py` armed for implementation plans, never for review/fold loops.
- **Sixth instance, 2026-10-04 — nine idle hours:** round 7's Codex half dispatched as `nohup … &`; Codex finished
  three minutes later; the result sat unread for nine hours until the human asked.
