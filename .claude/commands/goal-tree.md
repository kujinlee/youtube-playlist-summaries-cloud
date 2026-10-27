---
description: Print the goal tree — every work thread in this session, hung under the request it serves, with live PR state
---

Print the **goal tree** for this session: the work-line view of *why* each thread exists, not just a list.
Asked for by the owner 2026-10-26: *"how i will be able to understand your goal if you do not show the
relationship of work threads (or lack there of)?"*

**Derive, never recall.** The tree's facts come from tools run now, not from memory or the handoff:

1. **The root is the owner's request, quoted** — the latest instruction that set the current goal. If
   more than one goal is live, print one tree per goal and say they are separate.
2. **Gather the threads:** `gh pr list --state open` (head SHA, `mergeStateStatus`, checks), the PRs merged
   this session (`git log --oneline origin/master` since the session's first merge), running background
   tasks, and backlog rows filed this session.
3. **Hang every thread under ONE relation branch**, and name the relation:
   - **fix**: directly serves the root (name the backlog row it fixes);
   - **blocker**: found while doing a fix and stopping it (say WHAT it blocked);
   - **bookkeeping**: records findings, no new behaviour;
   - **side question**: the owner's aside, and whether it is being worked.

   A thread that serves none of these is shown as **unrelated**, never folded in.
4. **Name each thread by its backlog row or PR, never `T1`/`T2`**: those numbers were reused across
   maps and confused the reader.
5. **State per leaf:** ✅ merged (SHA) · ⏳ in flight (what it waits on) · ⬜ next · ❌ blocked (on what).
   ⚠ If a `gh` call fails, say **CANNOT RUN** in the tree. Never print a state you did not just read.

Format: a fenced box-drawing tree (`├─ │ └─`), the root on top, one line per leaf. Then a one-line
**"What changed since the last tree"**, and close with the CHECK/RESULT table.

Step banners carry the same branch tag, so the transcript reads as this tree's history:
`[mm-dd hh:mm] ▶ [fix] backlog #223 · what`.
