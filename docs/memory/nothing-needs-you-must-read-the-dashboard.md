---
name: nothing-needs-you-must-read-the-dashboard
description: Before saying "nothing needs you", read the goal tree's NEEDS YOU list (the open ask files, the ledger, the backlog) — on 2026-10-27 the old dashboard held 37 asks while every summary I wrote said none
metadata:
  type: feedback
---
**The rule:** before writing "nothing needs you", run `python3 scripts/goal-tree.py` and read its NEEDS YOU
section: it reads the open ask files in `docs/asks/`, the in-flight ledger and the backlog, and says "nothing
waits on you" only when all three were read. Quote its count; a NOT READ source is not an all-clear.

## History

"Nothing needs you" was my closing line all day on 2026-10-27, derived from in-flight work only. The suite
inventory (backlog #384) measured three answers to "what needs me?": the dashboard's `unresolved()` returned
**37** (8 readable asks from 2026-09-09..29, plus **29** "could not read one ask"), the backlog page 12 rows
"need your decision", and my chat said 0. Nothing reconciles them.

**Why:** the owner skims the closing table; a false "nothing needs you" hides real asks — and stale ones
that nobody has triaged look identical to live ones.

**How to apply:** say "N items in NEEDS YOU (sources read: …), none new from this work" instead of "nothing".
The dashboard's per-PR entry rule and its store retired on 2026-11-25 (dashboard-retire S2) and the page
on 2026-11-26 (S3); asks are files in `docs/asks/` now. Related: [[a-check-result-is-not-the-claim]],
[[how-to-shape-a-message-to-me]].
