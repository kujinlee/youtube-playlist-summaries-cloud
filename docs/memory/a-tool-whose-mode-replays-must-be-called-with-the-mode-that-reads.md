---
name: a-tool-whose-mode-replays-must-be-called-with-the-mode-that-reads
description: "FIRES-WHEN: I call a repo tool and read its output as current state — goal-tree.py --page/--print without --snapshot REPLAYS the log; gen-backlog-page.parse takes a LIST of lines (a str gives a false ShapeError). Twice each on 2026-10-28 after I had recorded both."
metadata:
  type: feedback
---

**Two tools in this repo give a confident, WRONG answer when called the obvious way**, and on 2026-10-28 I hit
each one twice — once after I had written the lesson into the handoff.

- `scripts/goal-tree.py --page` / `--print` **replay the last logged snapshot**; only `--snapshot` reads the
  sources. I reported a "known defect" to a reviewer (11 decisions, not 10) that was a stale replay, and later
  read a stale tree after editing `docs/goal-threads.md`.
- `gen-backlog-page.parse` takes a **list of lines** (`text.split("\n")`). Given a str it raises a ShapeError
  that reads like "the backlog is broken" — I nearly reported master's backlog as malformed.

**Why:** both failures look like findings about the SUBJECT, not about my call, so they get believed.
**How to apply:** before reading a tool's output as current, check the call matches its signature/mode — run
`--snapshot`, pass lines; and when a "broken file" verdict disagrees with a gate that passes on the same file
(`check-features` was green), suspect the call first. Related: [[a-check-result-is-not-the-claim]].
