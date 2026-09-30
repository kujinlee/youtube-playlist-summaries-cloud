---
name: a-side-job-gets-a-name-first
description: "FIRES-WHEN: work arrives mid-session over ~5 tool calls or touching a tracked file — Work arriving mid-session gets a plan slug + branch BEFORE the first edit if it is over ~5 tool calls or touches a tracked file — the sentinel holds one plan, so announce the swap"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ad53fab4-5d76-46c5-b5e1-641e077c8679
  modified: 2026-09-22T20:30:16.639Z
---

Something arriving mid-session — a user complaint, a defect you tripped over, a blocker — is a
**side job**. Ask one question first: **more than about five tool calls, or does it touch a tracked
file?** No → do it inline, say what you are doing in a clause. **Yes → it gets a plan slug AND a
branch before the first edit**; a backlog row only if you are DEFERRING it (filing what you will do
in ten minutes is bookkeeping; filing what you will not do is the point).

**Why:** on 2026-09-22 a user-reported Stop-hook defect ran to completion across three guards — ~40
tool calls, three suites, nine mutations — with **no plan armed, no branch named, and no banner
emitted**. The user could not tell which of two live threads any line belonged to. ⭐ The chain is
the lesson, because *"remember to banner"* would not have broken it: `CLAUDE.md` says to DERIVE the
thread name from the plan slug, the other thread owned the sentinel and was paused, so there was no
slug — and the response was to stop bannering **entirely** rather than notice the gap. A convention
with an unnamed precondition fails silently when that precondition does.

**How to apply — SAME TREE:** a switch costs pause → arm → finish → re-arm. `--pause` with a reason
that NAMES THE PLAN FILE to return to (the next turn will not remember it), banner the switch with
`⤳ SWITCHED from <old> (state) → <new>` and `↳ RESUMED <old>`, and restore with
`--plan .claude/plans/<slug>.md`, which preserves ticks.

⟳ **A WORKTREE IS DIFFERENT, AND MY FIRST VERSION OF THIS SAID OTHERWISE.** It claimed the sentinel
supervises exactly ONE plan and two threads cannot both be armed — **measured false hours later,
with both armed at once**: `begin-plan.py` resolves `ROOT` from its own path, so every tree has a
private sentinel. ⛔ But the real limit is worse than the one I invented: only ONE TREE IS
SUPERVISED. `block-idle-stop.sh` derives `REPO_ROOT` from its own path and the session runs the
hook under its cwd, so a worktree plan buys a thread NAME for banners and **no premature-stop
protection at all**. Use a worktree to isolate a tree from an in-flight sweep or a live agent — not
as a way to supervise two threads. See [[check-the-assumption-not-just-the-code]]: I generalised a
constraint from one observation instead of reading the mechanism, inside a rule about unexamined
preconditions failing silently.

Rule: `docs/process-checklists.md` → *A SIDE JOB gets a name before it gets work*. Evidence:
`docs/process-rationale.md` → *The side job with no name*. Guard: `check-banner-armed.py`'s
`unheralded` class is the mechanical half — read its threshold, never recall it. See
[[the-user-does-not-follow-in-real-time]] for why the banner exists at all, and
[[a-convention-catches-what-you-read]] for why the prose alone was never going to hold.

⚠ Not enforced, and do not imply otherwise: nothing checks that slug, branch and row describe the
same job, and nothing detects a side job that starts under the bar and grows past it. Ask the size
question again when it grows.
