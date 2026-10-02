---
name: backlog-110-parser-completeness-merged
description: "FIRES-WHEN: citing backlog #110 or PR #287 — ⭐ Backlog #110 — PR #287 open. 4 rounds; BOTH Blockings were the row's own defect reintroduced by its own fix. Report population must EQUAL read population"
metadata: 
  node_type: memory
  type: project
  originSessionId: 24bed3bc-51b2-4b47-b1fe-a488b2d3db19
  modified: 2026-09-10T19:21:28.519Z
---

✅ **MERGED 2026-09-10 as `050913f6`** (PR #287, squashed, branch deleted). CI green on the PR
and the gates re-run on master after the squash: 165/165 · 59/59 · 89/89 · all ratchets rc=0 ·
113 backlog rows, 0 unread. ⚠ It carries TWO subjects — #110 and the selection-card guard
([[selection-card-guard-built]]) — 8 review rounds, 14 halves, 8 commits.
`gen-backlog-page` suite **86 → 165**; `--mutate .` **37 files / 412
mutations / 0 survivors** at the final commit (the number moved twice after this line was
first written — which is the stale-count class this very branch kept fixing in prose).

**The defect:** `gen-backlog-page.parse()` skipped any line failing `^\|\s*\d+\s*\|` in silence, so a
number cell with a `⭐`, a `#` or one leading space dropped its item off the page and off every count.
The completeness case could not see it — expectation and subject both came out of `parse()`.

⭐⭐ **THE FIX IS AN INVARIANT, NOT A PREDICATE, and this is the durable part.** Two failed designs
came first, each an *allowlist of malformations* ("does this line LOOK like a row?"), and reviewers
defeated both by naming a spelling the list did not have. What worked: **the report population must
EQUAL the read population**, asserted by running the same input twice — once plain, once decorated —
and requiring that wherever the plain row is READ, the decorated one is REPORTED. Six contexts,
non-vacuous in both directions.

⭐ **BOTH Blockings were this row's own defect reintroduced by its own fix** (`portable-practices` §12,
twice in one branch):
* **r2** — I put fence-skipping in the READ path to silence a false positive in the REPORT. One stray
  ` ``` ` then dropped **61 of 110 rows**, silently, exit 0. *Lesson: check which path a fix lives in.
  Trading "the warning is noisy" for "rows disappear" is never right.*
* **r3** — narrowed the report to a contiguous block while reading stayed section-wide, so `| ⭐111 |`
  vanished exactly where `| 111 |` rendered, **with the branch's own new ratchet green over it**.

⚠ **A reviewer finding can need REVERSING later.** r1 asked for a legend table in the Items section to
report nothing; satisfying that caused r3's Blocking. It is now deliberately reported, with the
reversal recorded in the case that pins it. A finding is evidence, not a specification.

**Also fixed, PRE-EXISTING (reproduced on master in a throwaway worktree):** `dependency_svg` indexed
`by_num[n]` for every number `DEPENDS` names, so an unread dependency row raised `KeyError` inside
`build` and **no page was written at all**. Found by decorating a *different* row than the one being
tested — the population of your own test inputs matters as much as the code's.

**Delivery had no falsifier at all** until r2/r3 measured it: the page box, the terminal report and the
⚠-prefix split could each be deleted with a green suite. Fixed by running `main()` inside the suite,
one `drift_notes_for` for page and terminal (they had drifted — the terminal said "no longer open"
about an OPEN item), and one `report_run` on both success arms.

See also [[a-report-format-is-a-contract]] (§22 came out of this), [[backlog-md-stays-markdown]],
[[fixing-a-premise-is-not-covering-the-branch]], [[a-filed-finding-s-proposed-fix-is-a-hypothesis]].
