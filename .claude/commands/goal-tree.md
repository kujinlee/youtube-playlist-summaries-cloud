---
description: Print the goal tree — every work thread in this session, hung under the request it serves, with live PR state
---

Print the **goal tree** for this session: the work-line view of *why* each thread exists, not just a list.
Asked for by the owner 2026-10-26: *"how i will be able to understand your goal if you do not show the
relationship of work threads (or lack there of)?"*

**Run the logger FIRST, and print what it printed** (backlog #363), so the chat and the page agree:

```bash
python3 scripts/goal-tree.py --snapshot --page --print
```

It reads the RELATIONS from `docs/goal-threads.md` and DERIVES every leaf's state from `git log origin/master`,
`gh pr list` and `.claude/inflight.jsonl`; it logs the snapshot to `docs/goal-tree-log.jsonl` only when the tree
changed, and rebuilds http://127.0.0.1:7391/goal-tree (current tree on top, timeline of changes below).

1. **The tree is the script's output, not mine.** Copy its tree into a fenced block unchanged. ⛔ If it exits 2
   (CANNOT RUN), say so above the tree — its leaves then read CANNOT RUN and nothing was logged. If it exits 1,
   `docs/goal-threads.md` is malformed: fix the line it names and run it again.
2. **A thread the file does not declare is the one thing to add by hand.** Check this session's threads
   against `docs/goal-threads.md` (`gh pr list --state open`, PRs merged this session, background tasks,
   backlog rows filed) and add any missing one under its goal — the root is the owner's request, quoted with its
   time; each thread gets ONE relation — then run the command again (the edit itself also triggers a snapshot):
   - **fix**: directly serves the root (name the backlog row it fixes);
   - **blocker**: found while doing a fix and stopping it (say WHAT it blocked);
   - **bookkeeping**: records findings, no new behaviour;
   - **side**: the owner's aside.

   An open PR no goal names is printed under **UNDECLARED** by the script, never folded in.
3. **Name each thread by its backlog row or PR, never `T1`/`T2`**: those numbers were reused across maps and
   confused the reader. The file's grammar refuses a thread that names neither.
4. **States are the script's:** ✅ merged (SHA) · ⏳ open or in flight · ⬜ next · ❌ waits (declared) · ✖ closed ·
   ⚠ CANNOT RUN. Never print a state the script did not just read.

Format: a fenced box-drawing tree (`├─ │ └─`), the root on top, one line per leaf. Then a one-line
**"What changed since the last tree"** (the page's newest timeline entry), and close with the CHECK/RESULT table.

Step banners carry the same branch tag, so the transcript reads as this tree's history:
`[mm-dd hh:mm] ▶ [fix] backlog #223 · what`.
