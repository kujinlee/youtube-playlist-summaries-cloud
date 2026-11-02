---
name: parallel-threads-need-a-thread-map
description: "FIRES-WHEN: two or more threads/PRs are in flight at once (reviews in background, a side job, an audit) — banners lapse exactly then"
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6abe358-4c0b-44cb-a058-5446372998ef
  modified: 2026-10-27T02:37:47.250Z
---

⛔ **When several threads run at once, banners are what lapses — and that is when they matter most.**
2026-10-26: PR #402's review loop, a 164-row backlog audit and a fix batch ran interleaved; I stopped
emitting banners and the user said *"You are pursuing several threads of works and you stopped emitting
banner. I am having difficulty in following your works."* Then: *"You may use simplified banner for brevity."*

⛔⛔ **2026-10-26 evening, the map itself was not enough:** *"how i will be able to understand your goal if
you do not show the relationship of work threads (or lack there of)? I am reading transcript and get
puzzled"* — and *"where T1 to T6 are created from?"*. A flat T1..Tn list hides WHY each thread exists, and
T-numbers were RE-USED across maps (T2 meant different work before and after compaction).

**How to apply:**
- The map is a **GOAL TREE**, not a list: root = the user's actual request, quoted; each thread hangs under
  a branch that names its RELATION — *fix* (directly serves the goal) · *blocker* (found while doing it;
  say what it blocked) · *bookkeeping* (records findings) · *side question* (user's aside). Unrelated work
  is shown as unrelated.
- **Name threads by their backlog row / PR, never T1/T2** — a stable id cannot be re-used.
- Every step gets a ONE-LINE banner carrying the branch: `` `[mm-dd hh:mm] ▶ [fix] backlog #223 · what` ``.
- A switch gets one line saying WHY (e.g. "→ [blocker] CI red on ffmpeg").
- A thread switch or a background notification still gets its line — the switch is what the reader loses.
- Re-print the map whenever a thread is added, finishes, or merges.

See [[the-user-does-not-follow-in-real-time]], [[waiting-lines-carry-a-timestamp]].
