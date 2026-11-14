---
name: a-side-job-gets-a-name-first
description: "FIRES-WHEN: work arrives mid-session (a complaint, a defect tripped over, a blocker) that is over ~5 tool calls or touches a tracked file — give it a plan slug + branch BEFORE the first edit, and banner the swap"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ad53fab4-5d76-46c5-b5e1-641e077c8679
  modified: 2026-09-22T20:30:16.639Z
---

**The rule: a side job arriving mid-session gets one question first — more than about five tool calls, or does it touch a tracked file? No → do it inline, say what you are doing in a clause. Yes → it gets a plan slug AND a branch before the first edit;** a backlog row only if you are DEFERRING it (filing what you will do in ten minutes is bookkeeping).

**How to apply — same tree:** pause → arm → finish → re-arm. `begin-plan.py --pause` with a reason that NAMES THE PLAN FILE to return to (the next turn will not remember it); banner `⤳ SWITCHED from <old> (state) → <new>` and later `↳ RESUMED <old>`; restore with `--plan <path>`, which preserves ticks.

**Worktrees:** each tree has a private sentinel (`begin-plan.py` resolves `ROOT` from its own path), so two plans CAN be armed at once — but only ONE TREE IS SUPERVISED: `block-idle-stop.sh` derives `REPO_ROOT` from its own path and runs under the session's cwd. A worktree plan buys a thread NAME for banners and **no premature-stop protection**. Use a worktree to isolate a tree, not to supervise two threads.

**Why:** 2026-09-22, a user-reported Stop-hook defect ran across three guards — ~40 tool calls, three suites, nine mutations — with no plan, no branch and no banner; the user could not tell which of two live threads any line belonged to. CLAUDE.md derives the thread name from the plan slug; the other thread owned the (paused) sentinel, so there was no slug — and I stopped bannering entirely. A convention with an unnamed precondition fails silently when that precondition does.

Rule: `docs/process-checklists.md` → *A SIDE JOB gets a name before it gets work*. Evidence: `docs/process-rationale.md` → *The side job with no name*. Guard: `check-banner-armed.py`'s `unheralded` class — read its threshold, never recall it.

⚠ Not enforced: nothing checks that slug, branch and row describe the same job, or detects a side job that starts under the bar and grows past it. Ask the size question again when it grows.

## History

- My first version claimed the sentinel supervises exactly ONE plan, so two threads cannot both be armed — measured false hours later with both armed; the real limit (one supervised TREE) is the worktree paragraph above. I had generalised from one observation instead of reading the mechanism ([[check-the-assumption-not-just-the-code]]).

Related: [[the-user-does-not-follow-in-real-time]] (why the banner exists), [[a-convention-catches-what-you-read]] (why prose alone would not hold).
