---
name: nothing-needs-you-must-read-the-dashboard
description: Before saying "nothing needs you", read the dashboard's unresolved asks — on 2026-10-27 it held 37 while every summary I wrote said none
metadata:
  type: feedback
---
"Nothing needs you" was my closing line all day on 2026-10-27, derived from in-flight work only. The suite
inventory (backlog #384) measured three answers to "what needs me?": the dashboard's `unresolved()` returned
**37** (8 readable asks from 2026-09-09..29, plus **29** "could not read one ask"), the backlog page 12 rows
"need your decision", and my chat said 0. Nothing reconciles them.

**Why:** the owner skims the closing table; a false "nothing needs you" hides real asks — and stale ones
that nobody has triaged look identical to live ones.

**How to apply:** before writing "nothing needs you", regenerate `/dashboard` (`python3 scripts/gen-dashboard.py`)
and read its *What needs you* count; say "N open asks on the dashboard (M unreadable), none new from this
work" instead of "nothing", until #384 gives one definition of "needs you". Related: [[a-check-result-is-not-the-claim]],
[[how-to-shape-a-message-to-me]].
